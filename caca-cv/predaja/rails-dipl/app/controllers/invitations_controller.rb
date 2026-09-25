class InvitationsController < ApplicationController
  before_action :set_trip, only: [:create]
  before_action :authorize_trip_access!, only: [:create]
  before_action :set_invitation, only: [:accept, :decline]

  def index
    @pending_invitations = TripInvitation.pending_for(current_user)
      .includes(trip: :creator)
      .order(created_at: :desc)
  end

  def create
    authorize trip, :invite?

    @invite_result = ::Trips::InvitationSender.new(
      trip: trip,
      email: params[:invitation][:email],
      invited_by: current_user
    ).call

    respond_to do |format|
      format.turbo_stream
      format.html do
        if @invite_result[:success]
          redirect_to trip_path(trip), notice: t("invitations.sent")
        else
          redirect_to trip_path(trip), alert: @invite_result[:error]
        end
      end
    end
  end

  def accept
    trip = invitation.trip
    ActiveRecord::Base.transaction do
      trip.trip_participants.find_or_create_by!(user: current_user)
      invitation.update!(accepted_at: Time.current)
    end
    broadcast_invite_section(trip)
    redirect_to trip_path(trip), notice: t("invitations.accepted")
  end

  def decline
    trip = invitation.trip
    invitation.destroy!
    broadcast_invite_section(trip)
    redirect_to invitations_path, notice: t("invitations.declined")
  end

  private

  attr_reader :trip, :invitation

  def set_trip
    @trip = Trip.find(params[:invitation][:trip_id])
  end

  def authorize_trip_access!
    authorize trip, :show?
  end

  def broadcast_invite_section(trip)
    trip_dom_id = ActionView::RecordIdentifier.dom_id(trip)
    Turbo::StreamsChannel.broadcast_replace_to(
      "#{trip_dom_id}_notifications",
      target: ActionView::RecordIdentifier.dom_id(trip, :invite_section),
      partial: "trips/invitations/invite_section",
      locals: { trip: Trip.find(trip.id) }
    )
  end

  def set_invitation
    @invitation = TripInvitation.pending_for(current_user).find(params[:id])
  rescue ActiveRecord::RecordNotFound
    redirect_to invitations_path, alert: t("invitations.not_found")
  end
end
