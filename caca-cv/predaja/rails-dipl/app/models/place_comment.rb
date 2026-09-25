# == Schema Information
#
# Table name: place_comments
#
#  id         :bigint           not null, primary key
#  body       :text             not null
#  created_at :datetime         not null
#  updated_at :datetime         not null
#  place_id   :bigint           not null
#  user_id    :bigint           not null
#
# Indexes
#
#  index_place_comments_on_place_id  (place_id)
#  index_place_comments_on_user_id   (user_id)
#
# Foreign Keys
#
#  fk_rails_...  (place_id => places.id) ON DELETE => cascade
#  fk_rails_...  (user_id => users.id) ON DELETE => cascade
#
class PlaceComment < ApplicationRecord
  include ActionView::RecordIdentifier

  belongs_to :place
  belongs_to :user

  validates :body, presence: true

  after_create_commit :broadcast_append_comment
  after_destroy_commit :broadcast_remove_comment

  private

  def broadcast_append_comment
    broadcast_append_to [ place.trip, :places ],
      target: dom_id(place, :comments),
      partial: "trips/places/comments/comment",
      locals: { comment: self, trip: place.trip, place: place }
  end

  def broadcast_remove_comment
    broadcast_remove_to [ place.trip, :places ], target: self
  end
end
