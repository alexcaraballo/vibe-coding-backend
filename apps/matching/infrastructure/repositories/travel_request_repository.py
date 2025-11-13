"""SQLAlchemy implementation of TravelRequestRepository."""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import select, delete as sql_delete, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.matching.domain.models import TravelRequest, TravelRequestStatus
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.matching.infrastructure.persistence.models import TravelRequestORM


class TravelRequestRepository(ITravelRequestRepository):
    """Implementación SQLAlchemy del repositorio de peticiones de viaje"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, travel_request: TravelRequest) -> TravelRequest:
        """Crea petición en base de datos"""
        # Convert domain to ORM
        orm_model = TravelRequestORM(
            passenger_id=travel_request.passenger_id,
            origin_lat=travel_request.origin_lat,
            origin_lng=travel_request.origin_lng,
            destination_lat=travel_request.destination_lat,
            destination_lng=travel_request.destination_lng,
            origin_address=travel_request.origin_address,
            destination_address=travel_request.destination_address,
            travel_date=travel_request.travel_date,
            time_from=travel_request.time_from,
            time_to=travel_request.time_to,
            seats_requested=travel_request.seats_requested,
            passenger_notes=travel_request.passenger_notes,
            status=travel_request.status.value,
            matched_trip_id=travel_request.matched_trip_id,
            created_at=travel_request.created_at
        )

        self.session.add(orm_model)
        await self.session.flush()
        await self.session.refresh(orm_model)

        # Convert back to domain
        return self._to_domain(orm_model)

    async def get_by_id(self, request_id: int) -> Optional[TravelRequest]:
        """Obtiene por ID"""
        stmt = select(TravelRequestORM).where(TravelRequestORM.id == request_id)
        result = await self.session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            return self._to_domain(orm_model)
        return None

    async def get_by_passenger(
        self,
        passenger_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[TravelRequest]:
        """Obtiene peticiones de un pasajero"""
        stmt = (
            select(TravelRequestORM)
            .where(TravelRequestORM.passenger_id == passenger_id)
            .order_by(TravelRequestORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._to_domain(orm) for orm in orm_models]

    async def get_pending_by_date(self, travel_date: date) -> list[TravelRequest]:
        """Obtiene peticiones pendientes para una fecha"""
        stmt = (
            select(TravelRequestORM)
            .where(
                TravelRequestORM.travel_date == travel_date,
                TravelRequestORM.status == TravelRequestStatus.PENDING.value
            )
        )
        result = await self.session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._to_domain(orm) for orm in orm_models]

    async def update(self, request_id: int, travel_request: TravelRequest) -> bool:
        """Actualiza petición"""
        travel_request.updated_at = datetime.utcnow()

        stmt = (
            sql_update(TravelRequestORM)
            .where(TravelRequestORM.id == request_id)
            .values(
                origin_lat=travel_request.origin_lat,
                origin_lng=travel_request.origin_lng,
                destination_lat=travel_request.destination_lat,
                destination_lng=travel_request.destination_lng,
                origin_address=travel_request.origin_address,
                destination_address=travel_request.destination_address,
                travel_date=travel_request.travel_date,
                time_from=travel_request.time_from,
                time_to=travel_request.time_to,
                seats_requested=travel_request.seats_requested,
                passenger_notes=travel_request.passenger_notes,
                status=travel_request.status.value,
                matched_trip_id=travel_request.matched_trip_id,
                updated_at=travel_request.updated_at
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete(self, request_id: int) -> bool:
        """Elimina petición"""
        stmt = sql_delete(TravelRequestORM).where(TravelRequestORM.id == request_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    def _to_domain(self, orm_model: TravelRequestORM) -> TravelRequest:
        """Convierte ORM a dominio"""
        return TravelRequest(
            id=orm_model.id,
            passenger_id=orm_model.passenger_id,
            origin_lat=orm_model.origin_lat,
            origin_lng=orm_model.origin_lng,
            destination_lat=orm_model.destination_lat,
            destination_lng=orm_model.destination_lng,
            origin_address=orm_model.origin_address,
            destination_address=orm_model.destination_address,
            travel_date=orm_model.travel_date,
            time_from=orm_model.time_from,
            time_to=orm_model.time_to,
            seats_requested=orm_model.seats_requested,
            passenger_notes=orm_model.passenger_notes,
            status=TravelRequestStatus(orm_model.status),
            matched_trip_id=orm_model.matched_trip_id,
            created_at=orm_model.created_at,
            updated_at=orm_model.updated_at
        )
