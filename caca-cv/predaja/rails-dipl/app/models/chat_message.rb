# == Schema Information
#
# Table name: chat_messages
#
#  id         :bigint           not null, primary key
#  content    :text
#  plan_json  :jsonb
#  role       :string           default("user"), not null
#  status     :integer          default("processing"), not null
#  created_at :datetime         not null
#  updated_at :datetime         not null
#  trip_id    :bigint           not null
#
# Indexes
#
#  index_chat_messages_on_trip_id                 (trip_id)
#  index_chat_messages_on_trip_id_and_created_at  (trip_id,created_at)
#
# Foreign Keys
#
#  fk_rails_...  (trip_id => trips.id)
#
class ChatMessage < ApplicationRecord
  belongs_to :trip

  enum :status, { processing: 0, done: 1, failed: 2 }

  after_create_commit -> { broadcast_append_to "trip_#{trip_id}_chat", target: "chat_messages", partial: "trips/chat_messages/message", locals: { message: self } }
  after_update_commit -> { broadcast_replace_to "trip_#{trip_id}_chat", target: dom_id(self), partial: "trips/chat_messages/message", locals: { message: self } }

  def has_plan?
    plan_json&.dig("plan", "days")&.any?
  end
end
