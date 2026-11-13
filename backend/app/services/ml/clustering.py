import uuid
from collections import Counter
from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from app.core.exceptions import DataLensException
from app.schemas.ml import ClusterProfile, SegmentationResponse


class SegmentationService:
    """
    Unsupervised customer and business segmentation using K-Means and Hierarchical clustering.
    Provides feature scaling, cluster profiling, silhouette validation, and ethical safeguards.
    """

    PROHIBITED_ATTRIBUTES = {
        "race", "ethnicity", "religion", "gender", "sex", "orientation",
        "disability", "ssn", "social_security", "password"
    }

    @classmethod
    def segment_dataset(
        cls,
        records: list[dict[str, Any]],
        feature_columns: list[str],
        algorithm: str = "kmeans",
        cluster_count: int = 3,
        scale_features: bool = True,
        cluster_label_prefix: str = "Segment",
        model_run_id: uuid.UUID | None = None,
        dataset_id: uuid.UUID | None = None,
        dataset_version_id: uuid.UUID | None = None,
        duration_ms: int = 0,
    ) -> SegmentationResponse:
        """
        Executes clustering algorithm across selected feature columns.
        """
        # 1. Ethical feature screening
        for col in feature_columns:
            if col.lower() in cls.PROHIBITED_ATTRIBUTES:
                raise DataLensException(
                    f"Feature '{col}' is a sensitive attribute and is strictly prohibited from clustering models.",
                    code="ETHICAL_VIOLATION",
                )

        if not records:
            raise DataLensException("Dataset contains zero records.", code="INSUFFICIENT_DATA")

        # 2. Extract and sanitize feature matrix
        matrix = []
        valid_indices = []

        for idx, row in enumerate(records):
            row_vals = []
            has_nan = False
            for col in feature_columns:
                val = row.get(col)
                if val is None:
                    has_nan = True
                    break
                try:
                    row_vals.append(float(val))
                except (ValueError, TypeError):
                    has_nan = True
                    break

            if not has_nan:
                matrix.append(row_vals)
                valid_indices.append(idx)

        if len(matrix) < max(10, cluster_count * 2):
            raise DataLensException(
                f"Insufficient valid numerical observations for clustering. Found {len(matrix)} complete rows, "
                f"but at least {max(10, cluster_count * 2)} are required for {cluster_count} clusters.",
                code="INSUFFICIENT_DATA",
            )

        X_orig = np.array(matrix, dtype=np.float64)
        total_valid = len(X_orig)

        # 3. Optional standardization
        if scale_features:
            scaler = StandardScaler()
            X = scaler.fit_transform(X_orig)
        else:
            X = X_orig

        # 4. Fit clustering model
        k = max(2, min(cluster_count, total_valid - 1))
        inertia = None

        if algorithm == "kmeans":
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            inertia = float(kmeans.inertia_)
            method_desc = (
                f"K-Means clustering iteratively assigns observations to {k} cluster centroids "
                f"to minimize within-cluster sum of squares (Inertia: {inertia:.1f})."
            )
        elif algorithm == "hierarchical":
            agg = AgglomerativeClustering(n_clusters=k, metric="euclidean", linkage="ward")
            labels = agg.fit_predict(X)
            method_desc = (
                f"Hierarchical agglomerative clustering sequentially merges nearest pairs of observations "
                f"using Ward's minimum variance criterion into {k} clusters."
            )
        else:
            raise DataLensException(f"Unsupported clustering algorithm '{algorithm}'.", code="INVALID_ALGORITHM")

        # 5. Compute silhouette validation score if population permits
        sil_score = None
        if total_valid >= k * 3 and total_valid <= 20000:
            try:
                sil_score = round(float(silhouette_score(X, labels)), 3)
            except Exception:
                sil_score = None

        # 6. Profile each cluster in original feature space
        label_counts = Counter(labels)
        profiles: list[ClusterProfile] = []

        overall_means = np.mean(X_orig, axis=0)

        for c_id in sorted(label_counts.keys()):
            mask = labels == c_id
            c_data = X_orig[mask]
            count = len(c_data)
            pct = round((count / total_valid) * 100, 1)

            means = np.mean(c_data, axis=0)
            minima = np.min(c_data, axis=0)
            maxima = np.max(c_data, axis=0)

            f_means = {col: round(float(m), 2) for col, m in zip(feature_columns, means, strict=False)}
            f_mins = {col: round(float(m), 2) for col, m in zip(feature_columns, minima, strict=False)}
            f_maxs = {col: round(float(m), 2) for col, m in zip(feature_columns, maxima, strict=False)}

            # Generate descriptive characterization
            key_traits = []
            for col, m, overall_m in zip(feature_columns, means, overall_means, strict=False):
                if overall_m != 0:
                    diff_pct = ((m - overall_m) / abs(overall_m)) * 100
                    if diff_pct > 15:
                        key_traits.append(f"High {col} (+{diff_pct:.0f}%)")
                    elif diff_pct < -15:
                        key_traits.append(f"Low {col} ({diff_pct:.0f}%)")

            trait_str = ", ".join(key_traits) if key_traits else "Average distribution across metrics"

            profiles.append(
                ClusterProfile(
                    cluster_id=int(c_id),
                    cluster_name=f"{cluster_label_prefix} {c_id + 1}",
                    record_count=count,
                    percentage=pct,
                    feature_means=f_means,
                    feature_minima=f_mins,
                    feature_maxima=f_maxs,
                    characterization=trait_str,
                )
            )

        caveats = [
            "Clusters reflect mathematical feature groupings and should not be assumed to constitute immutable customer personas.",
            "Changes in feature distribution or scaling parameters will alter cluster boundaries.",
            f"Silhouette score is {sil_score if sil_score is not None else 'N/A'} (scale: -1.0 to +1.0).",
        ]

        summary_text = (
            f"Segmented {total_valid} observations across {len(feature_columns)} features into {k} clusters. "
            f"Largest cluster is '{profiles[0].cluster_name}' ({profiles[0].percentage}%), characterized by {profiles[0].characterization}."
        )

        return SegmentationResponse(
            model_run_id=model_run_id or uuid.uuid4(),
            dataset_id=dataset_id or uuid.uuid4(),
            dataset_version_id=dataset_version_id or uuid.uuid4(),
            algorithm=algorithm,
            cluster_count=k,
            total_records_clustered=total_valid,
            feature_columns=feature_columns,
            clusters=profiles,
            silhouette_score=sil_score,
            inertia=round(inertia, 2) if inertia is not None else None,
            segment_comparison_summary=summary_text,
            method_explanation=method_desc,
            caveats_and_limitations=caveats,
            execution_time_ms=duration_ms,
        )
