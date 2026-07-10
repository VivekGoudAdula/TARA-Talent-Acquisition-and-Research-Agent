"""Input bundle for behaviour analytics."""

from pydantic import BaseModel

from app.schemas.customer360 import CustomerAggregate, Customer360ProfileResponse
from app.schemas.financial_profile import FinancialProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile


class BehaviourAnalyticsInput(BaseModel):
    """All inputs required by the Behaviour Analytics Engine."""

    aggregate: CustomerAggregate
    financial: FinancialProfile
    transaction: TransactionAnalyticsProfile
    profile: Customer360ProfileResponse
