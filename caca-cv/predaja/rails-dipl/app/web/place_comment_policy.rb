class PlaceCommentPolicy < ApplicationPolicy
  def create?
    participant?
  end

  def destroy?
    participant? && record.user_id == user.id
  end

  private

  def participant?
    record.place.trip.participants.include?(user)
  end
end
