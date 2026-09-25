# == Schema Information
#
# Table name: trips
#
#  id                       :bigint           not null, primary key
#  accommodation_address    :string
#  accommodation_details    :text
#  accommodation_latitude   :decimal(10, 6)
#  accommodation_longitude  :decimal(10, 6)
#  arrival_at               :datetime
#  arrival_details          :string
#  arrival_transport_mode   :string
#  departure_at             :datetime
#  departure_details        :string
#  departure_transport_mode :string
#  destination              :string           not null
#  end_date                 :date             not null
#  start_date               :date             not null
#  status                   :integer          default("draft"), not null
#  title                    :string           not null
#  created_at               :datetime         not null
#  updated_at               :datetime         not null
#  creator_id               :bigint           not null
#
# Indexes
#
#  index_trips_on_creator_id  (creator_id)
#  index_trips_on_start_date  (start_date)
#  index_trips_on_status      (status)
#
# Foreign Keys
#
#  fk_rails_...  (creator_id => users.id) ON DELETE => cascade
#
class Trip < ApplicationRecord
  TRANSPORT_MODES = %w[plane bus train car ferry other].freeze

  enum :status, { draft: 0, planning: 1, finalized: 2, completed: 3 }

  belongs_to :creator, class_name: "User", inverse_of: :created_trips

  has_one_attached :cover_image

  has_many :trip_participants, dependent: :destroy
  has_many :participants, through: :trip_participants, source: :user
  has_many :trip_invitations, dependent: :destroy
  has_many :places, dependent: :destroy
  has_many :tickets, dependent: :destroy
  has_many :chat_messages, dependent: :destroy
  has_one :itinerary, dependent: :destroy

  validates :title, presence: true
  validates :destination, presence: true
  validates :start_date, presence: true
  validates :end_date, presence: true
  validates :arrival_transport_mode, inclusion: { in: TRANSPORT_MODES }, allow_blank: true
  validates :departure_transport_mode, inclusion: { in: TRANSPORT_MODES }, allow_blank: true
  validate :end_date_after_start_date

  before_save :reset_accommodation_coordinates, if: :accommodation_address_changed?

  scope :ordered_by_start_date, -> { order(start_date: :asc) }

  def duration_days
    (end_date - start_date).to_i + 1
  end

  def next_status
    { "draft" => "planning", "planning" => "finalized", "finalized" => "completed" }[status]
  end

  private

  def end_date_after_start_date
    return if start_date.blank? || end_date.blank?

    errors.add(:end_date, :after_start_date) if end_date < start_date
  end

  def reset_accommodation_coordinates
    self.accommodation_latitude = nil
    self.accommodation_longitude = nil
  end
end
