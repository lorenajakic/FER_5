# == Schema Information
#
# Table name: users
#
#  id                     :bigint           not null, primary key
#  confirmation_sent_at   :datetime
#  confirmation_token     :string
#  confirmed_at           :datetime
#  email                  :citext           default(""), not null
#  encrypted_password     :string           default(""), not null
#  name                   :string           not null
#  remember_created_at    :datetime
#  reset_password_sent_at :datetime
#  reset_password_token   :string
#  unconfirmed_email      :string
#  created_at             :datetime         not null
#  updated_at             :datetime         not null
#
# Indexes
#
#  index_users_on_confirmation_token    (confirmation_token) UNIQUE
#  index_users_on_email                 (email) UNIQUE
#  index_users_on_reset_password_token  (reset_password_token) UNIQUE
#
class User < ApplicationRecord
  devise :database_authenticatable, :registerable,
         :recoverable, :rememberable, :validatable, :confirmable

  has_one_attached :avatar

  has_many :trip_participants, dependent: :destroy
  has_many :trips, through: :trip_participants
  has_many :created_trips, class_name: "Trip", foreign_key: :creator_id,
                           inverse_of: :creator, dependent: :destroy
  has_many :places, foreign_key: :added_by_id, inverse_of: :added_by, dependent: :nullify
  has_many :place_comments, dependent: :destroy
  has_many :sent_invitations, class_name: "TripInvitation", foreign_key: :invited_by_id,
                              inverse_of: :invited_by, dependent: :destroy
  has_many :tickets, foreign_key: :uploaded_by_id, inverse_of: :uploaded_by, dependent: :destroy

  validates :name, presence: true
end
