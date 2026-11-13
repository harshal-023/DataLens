import uuid
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataLensException
from app.models.prompt_lab import PromptTemplate, PromptVersion
from app.schemas.prompt_lab import PromptVersionComparisonResponse, PromptVersionResponse


class PromptVersionService:
    """
    Manages immutable prompt versions. Once published, versions cannot be edited.
    """

    @classmethod
    async def create_version(
        cls,
        db: AsyncSession,
        prompt: PromptTemplate,
        system_prompt: str,
        user_prompt_template: str,
        variables: list[dict[str, Any]],
        model_config_snapshot: dict[str, Any],
        change_description: str,
        created_by_user_id: uuid.UUID | None,
    ) -> PromptVersion:
        """
        Calculates next version number and creates a new immutable version record.
        """
        # Get highest existing version number
        stmt = (
            select(func.coalesce(func.max(PromptVersion.version_number), 0))
            .where(PromptVersion.prompt_id == prompt.id)
        )
        current_max = (await db.execute(stmt)).scalar() or 0
        next_version = current_max + 1

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=next_version,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            variables=variables,
            model_config_snapshot=model_config_snapshot,
            change_description=change_description,
            created_by=created_by_user_id,
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)
        return version

    @classmethod
    async def get_versions_for_prompt(
        cls,
        db: AsyncSession,
        prompt_id: uuid.UUID,
    ) -> list[PromptVersion]:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(desc(PromptVersion.version_number))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_version_by_id(
        cls,
        db: AsyncSession,
        version_id: uuid.UUID,
    ) -> PromptVersion | None:
        stmt = select(PromptVersion).where(PromptVersion.id == version_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def compare_versions(
        cls,
        db: AsyncSession,
        prompt_id: uuid.UUID,
        version_id_a: uuid.UUID,
        version_id_b: uuid.UUID,
    ) -> PromptVersionComparisonResponse:
        v_a = await cls.get_version_by_id(db, version_id_a)
        v_b = await cls.get_version_by_id(db, version_id_b)

        if not v_a or not v_b:
            raise DataLensException("One or both prompt versions were not found.", code="VERSION_NOT_FOUND")

        if v_a.prompt_id != prompt_id or v_b.prompt_id != prompt_id:
            raise DataLensException("Versions do not belong to the requested prompt.", code="PROMPT_MISMATCH")

        sys_diff = v_a.system_prompt != v_b.system_prompt
        user_diff = v_a.user_prompt_template != v_b.user_prompt_template
        var_diff = v_a.variables != v_b.variables
        config_diff = v_a.model_config_snapshot != v_b.model_config_snapshot

        return PromptVersionComparisonResponse(
            prompt_id=prompt_id,
            version_a=PromptVersionResponse(
                id=v_a.id,
                prompt_id=v_a.prompt_id,
                version_number=v_a.version_number,
                system_prompt=v_a.system_prompt,
                user_prompt_template=v_a.user_prompt_template,
                variables=v_a.variables,
                model_config_snapshot=v_a.model_config_snapshot,
                change_description=v_a.change_description,
                created_by=v_a.created_by,
                created_at=v_a.created_at,
            ),
            version_b=PromptVersionResponse(
                id=v_b.id,
                prompt_id=v_b.prompt_id,
                version_number=v_b.version_number,
                system_prompt=v_b.system_prompt,
                user_prompt_template=v_b.user_prompt_template,
                variables=v_b.variables,
                model_config_snapshot=v_b.model_config_snapshot,
                change_description=v_b.change_description,
                created_by=v_b.created_by,
                created_at=v_b.created_at,
            ),
            system_prompt_diff=sys_diff,
            user_prompt_diff=user_diff,
            variables_diff=var_diff,
            model_config_diff=config_diff,
        )

    @classmethod
    async def restore_version(
        cls,
        db: AsyncSession,
        prompt: PromptTemplate,
        version_to_restore: PromptVersion,
        user_id: uuid.UUID | None,
    ) -> PromptVersion:
        """
        Restores an older version by creating a new version with the content of the target version.
        Guarantees that history is preserved and historical versions remain untouched.
        """
        change_desc = f"Restored from Version {version_to_restore.version_number}"
        return await cls.create_version(
            db=db,
            prompt=prompt,
            system_prompt=version_to_restore.system_prompt,
            user_prompt_template=version_to_restore.user_prompt_template,
            variables=version_to_restore.variables,
            model_config_snapshot=version_to_restore.model_config_snapshot,
            change_description=change_desc,
            created_by_user_id=user_id,
        )

