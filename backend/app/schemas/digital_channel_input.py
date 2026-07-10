"""Input bundle for digital & channel analytics."""

from pydantic import BaseModel

from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.customer360 import CustomerAggregate, Customer360ProfileResponse
from app.schemas.financial_profile import FinancialProfile
from app.schemas.relationship_analytics import RelationshipProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile


class DigitalChannelAnalyticsInput(BaseModel):
    aggregate: CustomerAggregate
    profile: Customer360ProfileResponse
    financial: FinancialProfile
    transaction: TransactionAnalyticsProfile
    behaviour: BehaviourProfile
    relationship: RelationshipProfile
