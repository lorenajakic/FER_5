# == Schema Information
#
# Table name: tickets
#
#  id             :bigint           not null, primary key
#  category       :integer          not null
#  cost_cents     :integer
#  cost_currency  :string           default("EUR")
#  date           :date
#  details        :text
#  title          :string           not null
#  created_at     :datetime         not null
#  updated_at     :datetime         not null
#  trip_id        :bigint           not null
#  uploaded_by_id :bigint           not null
#
# Indexes
#
#  index_tickets_on_trip_id               (trip_id)
#  index_tickets_on_trip_id_and_category  (trip_id,category)
#  index_tickets_on_uploaded_by_id        (uploaded_by_id)
#
# Foreign Keys
#
#  fk_rails_...  (trip_id => trips.id) ON DELETE => cascade
#  fk_rails_...  (uploaded_by_id => users.id) ON DELETE => cascade
#
class Ticket < ApplicationRecord
  MAX_FILE_SIZE = 20.megabytes
  ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp"
  ].freeze

  enum :category, { accommodation: 1, activity: 2, transport: 3, other: 4 }

  belongs_to :trip
  belongs_to :uploaded_by, class_name: "User", inverse_of: :tickets

  has_one_attached :file

  validates :title, presence: true
  validates :category, presence: true
  validate :file_must_exist
  validate :acceptable_file, if: -> { file.attached? }

  before_save { self.cost_currency = "EUR" if cost_currency.blank? }

  def cost
    cost_cents.present? ? cost_cents.to_f / 100 : nil
  end

  def cost=(value)
    self.cost_cents = value.present? ? (BigDecimal(value.to_s) * 100).round : nil
  end

  private

  def file_must_exist
    errors.add(:file, :blank) unless file.attached?
  end

  def acceptable_file
    unless ALLOWED_CONTENT_TYPES.include?(file.content_type)
      errors.add(:file, :invalid_type)
    end

    return unless file.byte_size > MAX_FILE_SIZE

    errors.add(:file, :too_large)
  end
end
