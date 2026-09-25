# == Schema Information
#
# Table name: itineraries
#
#  id         :bigint           not null, primary key
#  plan_json  :jsonb            not null
#  created_at :datetime         not null
#  updated_at :datetime         not null
#  trip_id    :bigint           not null
#
# Indexes
#
#  index_itineraries_on_trip_id      (trip_id)
#  index_itineraries_trip_id_unique  (trip_id) UNIQUE
#
# Foreign Keys
#
#  fk_rails_...  (trip_id => trips.id)
#
class Itinerary < ApplicationRecord
  belongs_to :trip

  def days
    plan_json&.dig("plan", "days") || []
  end

  def accommodation_location
    plan_json&.dig("accommodation_location")
  end
end
