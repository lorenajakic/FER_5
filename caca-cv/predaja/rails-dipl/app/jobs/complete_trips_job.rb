class CompleteTripsJob < ApplicationJob
  queue_as :default

  def perform
    Trip.finalized.where(end_date: ..Date.today).update_all(status: Trip.statuses[:completed])
  end
end
