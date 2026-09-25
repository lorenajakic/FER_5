class DashboardController < ApplicationController
  def index
    @trips = policy_scope(Trip).ordered_by_start_date.includes(participants: { avatar_attachment: :blob })
  end
end
