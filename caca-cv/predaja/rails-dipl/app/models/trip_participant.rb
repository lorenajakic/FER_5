# == Schema Information
#
# Table name: trip_participants
#
#  id         :bigint           not null, primary key
#  created_at :datetime         not null
#  updated_at :datetime         not null
#  trip_id    :bigint           not null
#  user_id    :bigint           not null
#
# Indexes
#
#  index_trip_participants_on_trip_id              (trip_id)
#  index_trip_participants_on_trip_id_and_user_id  (trip_id,user_id) UNIQUE
#  index_trip_participants_on_user_id              (user_id)
#
# Foreign Keys
#
#  fk_rails_...  (trip_id => trips.id) ON DELETE => cascade
#  fk_rails_...  (user_id => users.id) ON DELETE => cascade
#
class TripParticipant < ApplicationRecord
  belongs_to :trip
  belongs_to :user

  validates :user_id, uniqueness: { scope: :trip_id }
end
