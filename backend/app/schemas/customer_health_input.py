"""Input bundle for customer health analytics."""

from pydantic import BaseModel

from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.customer360 import CustomerAggregate, Customer360ProfileResponse
from app.schemas.digital_channel_analytics import DigitalChannelProfile
from app.schemas.financial_profile import FinancialProfile
from app.schemas.relationship_analytics import RelationshipProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile


class CustomerHealthAnalyticsInput(BaseModel):
    aggregate: CustomerAggregate
    profile: Customer360ProfileResponse
    financial: FinancialProfile
    transaction: TransactionAnalyticsProfile
    behaviour: BehaviourProfile
    relationship: RelationshipProfile
    digital: DigitalChannelProfile
