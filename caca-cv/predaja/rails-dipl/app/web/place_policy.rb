class PlacePolicy < ApplicationPolicy
  def create?
    participant?
  end

  def destroy?
    participant? && record.added_by_id == user.id
  end

  private

  def participant?
    record.trip.participants.include?(user)
  end
end
