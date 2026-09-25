# == Schema Information
#
# Table name: trip_invitations
#
#  id            :bigint           not null, primary key
#  accepted_at   :datetime
#  email         :citext           not null
#  created_at    :datetime         not null
#  updated_at    :datetime         not null
#  invited_by_id :bigint           not null
#  trip_id       :bigint           not null
#
# Indexes
#
#  index_trip_invitations_on_invited_by_id      (invited_by_id)
#  index_trip_invitations_on_trip_id            (trip_id)
#  index_trip_invitations_on_trip_id_and_email  (trip_id,email) UNIQUE
#
# Foreign Keys
#
#  fk_rails_...  (invited_by_id => users.id) ON DELETE => cascade
#  fk_rails_...  (trip_id => trips.id) ON DELETE => cascade
#
class TripInvitation < ApplicationRecord
  belongs_to :trip
  belongs_to :invited_by, class_name: "User", inverse_of: :sent_invitations

  validates :email, presence: true
  validates :email, uniqueness: { scope: :trip_id }

  scope :pending, -> { where(accepted_at: nil) }

  def self.pending_for(user)
    return none unless user

    pending.where(email: user.email.to_s.downcase.strip)
  end
end
