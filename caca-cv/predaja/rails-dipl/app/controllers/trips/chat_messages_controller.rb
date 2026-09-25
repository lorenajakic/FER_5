module Trips
  class ChatMessagesController < BaseController
    def index
      @messages = trip.chat_messages.order(:created_at, :id)
    end

    def create
      return redirect_to trip_path(trip) if content.blank?

      enqueue_agent_response
      respond_to do |format|
        format.turbo_stream { render turbo_stream: reset_form }
        format.html { redirect_to trip_chat_messages_path(trip) }
      end
    end

    private

    def content
      @content ||= params[:content].to_s.strip
    end

    def enqueue_agent_response
      user_msg  = trip.chat_messages.create!(role: "user", content:, status: :done)
      thinking  = trip.chat_messages.create!(role: "assistant", status: :processing)
      AgentChatJob.perform_later(thinking.id, user_msg.id)
    end

    def reset_form
      turbo_stream.replace("chat_input_form", partial: "trips/chat_messages/form", locals: { trip: })
    end
  end
end
