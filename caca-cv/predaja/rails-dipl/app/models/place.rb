# == Schema Information
#
# Table name: places
#
#  id                         :bigint           not null, primary key
#  address                    :string
#  category                   :integer          default("other"), not null
#  latitude                   :decimal(10, 7)   not null
#  longitude                  :decimal(10, 7)   not null
#  name                       :string           not null
#  created_at                 :datetime         not null
#  updated_at                 :datetime         not null
#  added_by_id                :bigint           not null
#  trip_id                    :bigint           not null
#
# Indexes
#
#  index_places_on_added_by_id  (added_by_id)
#  index_places_on_trip_id      (trip_id)
#
# Foreign Keys
#
#  fk_rails_...  (added_by_id => users.id) ON DELETE => cascade
#  fk_rails_...  (trip_id => trips.id) ON DELETE => cascade
#
class Place < ApplicationRecord
  enum :category, {
    restaurant: 0, museum: 1, park: 2, landmark: 3,
    shopping: 4, entertainment: 5, other: 6
  }

  belongs_to :trip
  belongs_to :added_by, class_name: "User", inverse_of: :places

  has_many :place_comments, dependent: :destroy

  validates :name, presence: true
  validates :latitude, presence: true, numericality: { greater_than_or_equal_to: -90, less_than_or_equal_to: 90 }
  validates :longitude, presence: true, numericality: { greater_than_or_equal_to: -180, less_than_or_equal_to: 180 }
  validates :category, presence: true

  after_create_commit :broadcast_prepend_to_places_list
  after_destroy_commit :broadcast_remove_from_places_list

  private

  def broadcast_prepend_to_places_list
    broadcast_prepend_to [ trip, :places ], target: "places_list", partial: "places/place", locals: { place: self }
  end

  def broadcast_remove_from_places_list
    return if trip.blank?

    broadcast_remove_to [ trip, :places ], target: self
  end
end
