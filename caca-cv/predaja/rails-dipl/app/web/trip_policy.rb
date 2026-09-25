class TripPolicy < ApplicationPolicy
  def show?
    participant?
  end

  def create?
    true
  end

  def update?
    creator? && editable?
  end

  def destroy?
    creator?
  end

  def update_status?
    creator? && !record.completed?
  end

  def invite?
    participant?
  end

  def permitted_attributes
    [
      :title, :destination, :start_date, :end_date, :cover_image,
      :accommodation_address, :accommodation_details,
      :arrival_transport_mode, :arrival_at, :arrival_details,
      :departure_transport_mode, :departure_at, :departure_details
    ]
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      scope.joins(:trip_participants).where(trip_participants: { user_id: user.id })
    end
  end

  private

  def participant?
    record.participants.exists?(id: user.id)
  end

  def creator?
    record.creator == user
  end

  def editable?
    record.draft? || record.planning?
  end
end
