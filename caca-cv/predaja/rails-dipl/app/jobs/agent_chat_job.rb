class AgentChatJob < ApplicationJob
  queue_as :default

  limits_concurrency(
    to: 1,
    key: ->(assistant_message_id, _user_message_id) { ChatMessage.where(id: assistant_message_id).pick(:trip_id) },
    duration: 10.minutes
  )

  def perform(assistant_message_id, user_message_id)
    assistant_msg = ChatMessage.find(assistant_message_id)
    trip = assistant_msg.trip

    history = trip.chat_messages
                  .where.not(id: [ assistant_message_id, user_message_id ])
                  .order(:created_at, :id)
                  .last(20)
                  .map { |m| { role: m.role, content: m.content } }

    user_message = ChatMessage.find(user_message_id).content

    result = Trips::AgentService.call(
      trip: trip,
      user_message: user_message,
      conversation_history: history,
      current_plan: trip.itinerary&.plan_json
    )
    persist_accommodation_location(trip, result)
    assistant_msg.update_columns(
      content: user_facing_message(result),
      plan_json: result["structured_response"].presence,
      status: ChatMessage.statuses[:done]
    )

    begin
      broadcast_message(assistant_msg, trip.id)
    rescue => e
      Rails.logger.error("[AgentChatJob] broadcast failed: #{e.class}: #{e.message}")
    end
  rescue => e
    Rails.logger.error("[AgentChatJob] #{e.class}: #{e.message}")
    msg = ChatMessage.find_by(id: assistant_message_id)
    return unless msg
    msg.update_columns(content: "Sorry, something went wrong. Please try again.", status: ChatMessage.statuses[:failed])
    broadcast_message(msg, msg.trip_id) rescue nil
  end

  private

  def persist_accommodation_location(trip, result)
    loc = result.dig("structured_response", "accommodation_location")
    lat = loc && loc["latitude"]
    lng = loc && loc["longitude"]
    return if lat.blank? || lng.blank?

    trip.update_columns(accommodation_latitude: lat, accommodation_longitude: lng)
  rescue => e
    Rails.logger.error("[AgentChatJob] persist accommodation location failed: #{e.class}: #{e.message}")
  end

  AGENT_ERROR_PREFIX = "Could not generate"

  def user_facing_message(result)
    msg = extract_message(result["message"]).presence || "Done."
    return msg unless msg.start_with?(AGENT_ERROR_PREFIX)

    Rails.logger.error("[AgentChatJob] agent returned error message: #{msg}")
    I18n.t("agent.errors.generic")
  end

  def extract_message(message)
    return message.select { |b| b["type"] == "text" }.map { |b| b["text"] }.join if message.is_a?(Array)
    message.presence
  end

  def broadcast_message(msg, trip_id)
    Turbo::StreamsChannel.broadcast_replace_to(
      "trip_#{trip_id}_chat",
      target: "chat_message_#{msg.id}",
      partial: "trips/chat_messages/message",
      locals: { message: msg }
    )
  end
end
