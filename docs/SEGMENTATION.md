# DataLens — Customer & Business Segmentation Methodology

## 1. Overview

DataLens Phase 3C provides unsupervised clustering algorithms (K-Means and Hierarchical Agglomerative Clustering) designed for cohort segmentation, behavioral profiling, and customer grouping across high-dimensional numerical feature spaces.

---

## 2. Algorithms & Implementation

### 2.1 Feature Preprocessing & Scaling

Clustering algorithms rely on Euclidean distances between feature vectors. If features have unequal variance or disparate units (e.g., Annual Spend in \$10,000s vs Purchase Frequency in single digits), unscaled distance metrics will be dominated by the larger unit.

DataLens applies `StandardScaler` normalization by default:
$$z = \frac{x - \mu}{\sigma}$$
Each feature is transformed to mean $\mu = 0$ and unit variance $\sigma = 1$.

---

### 2.2 K-Means Clustering

**Optimization Objective:**
Minimizes total within-cluster sum of squared errors (Inertia):
$$J = \sum_{k=1}^K \sum_{x_i \in C_k} \| x_i - \mu_k \|^2$$
where $\mu_k$ is the geometric centroid of cluster $C_k$.

**Algorithm Steps:**
1. Initializes $K$ cluster centers using K-Means++ seeding.
2. Assigns each observation to the nearest centroid.
3. Recalculates centroids as the arithmetic mean of all assigned points.
4. Repeats until centroid shifts fall below tolerance or maximum iterations ($300$) are reached.

---

### 2.3 Hierarchical Agglomerative Clustering

**Linkage Criterion:**
Constructs a hierarchical dendrogram by iteratively merging cluster pairs using Ward's minimum variance criterion:
$$\Delta \text{ESS} = \frac{n_A n_B}{n_A + n_B} \| \mu_A - \mu_B \|^2$$

---

## 3. Cluster Validation: Silhouette Analysis

DataLens computes the Silhouette Coefficient for every clustering run to provide objective mathematical quality assessment without relying on subjective guesswork:

For observation $i$:
- $a(i)$: Mean intra-cluster distance between $i$ and all other points in the same cluster.
- $b(i)$: Mean nearest-cluster distance between $i$ and all points in the closest neighboring cluster.

$$s(i) = \frac{b(i) - a(i)}{\max(a(i), b(i))}$$

The overall Silhouette Score is the mean $s(i)$ across all dataset observations, bounded in $[-1, +1]$:
- **$> 0.50$ (High Separation):** Strong, distinct clusters with clear mathematical boundaries.
- **$0.25 - 0.50$ (Moderate Overlap):** Natural customer segmentation with partial overlap.
- **$< 0.25$ (Diffuse Clusters):** Low separation; features may require re-engineering or different $K$.

---

## 4. Ethical Safeguards & Prohibited Attributes

To prevent algorithmic discrimination and ensure compliance with privacy regulations (GDPR, CCPA), DataLens enforces automated screening on feature inputs.

The system strictly rejects clustering requests containing any of the following protected attributes:
- `race`
- `ethnicity`
- `religion`
- `gender` / `sex`
- `orientation`
- `disability`
- `ssn` / `social_security`
- `password`

Attempting to include these attributes raises an immediate `ETHICAL_VIOLATION` error (`HTTP 422/400`).

