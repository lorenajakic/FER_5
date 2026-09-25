class TicketPolicy < ApplicationPolicy
  def show?
    participant?
  end

  def create?
    participant?
  end

  def update?
    destroy?
  end

  def destroy?
    participant? && (record.uploaded_by_id == user.id || record.trip.creator_id == user.id)
  end

  def permitted_attributes
    [ :title, :category, :date, :details, :cost_currency, :cost ]
  end

  private

  def participant?
    record.trip.participants.include?(user)
  end
end
