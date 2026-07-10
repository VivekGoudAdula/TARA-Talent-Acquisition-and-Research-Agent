"""Input bundle for relationship analytics."""

from pydantic import BaseModel

from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.customer360 import CustomerAggregate, Customer360ProfileResponse
from app.schemas.financial_profile import FinancialProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile


class RelationshipAnalyticsInput(BaseModel):
    aggregate: CustomerAggregate
    profile: Customer360ProfileResponse
    financial: FinancialProfile
    transaction: TransactionAnalyticsProfile
    behaviour: BehaviourProfile
