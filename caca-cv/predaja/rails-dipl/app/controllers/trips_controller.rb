class TripsController < ApplicationController
  before_action :set_trip, only: [ :show, :edit, :update, :destroy, :update_status ]

  def new
    @trip = Trip.new
    authorize trip
  end

  def create
    @trip = current_user.created_trips.build(trip_params)
    authorize trip

    if trip.save
      trip.trip_participants.create!(user: current_user)
      redirect_to trip, notice: t("trips.created")
    else
      render :new, status: :unprocessable_entity
    end
  end

  def show
    authorize trip
    redirect_to trip_places_path(trip)
  end

  def edit
    authorize trip
  end

  def update
    authorize trip

    if trip.update(trip_params)
      redirect_to trip, notice: t("trips.updated")
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    authorize trip
    trip.destroy!
    redirect_to root_path, notice: t("trips.deleted")
  end

  def update_status
    authorize trip
    next_status = trip.next_status
    if next_status
      trip.update!(status: next_status)
      redirect_to trip, notice: t("trips.status_updated", status: t("trips.statuses.#{next_status}"))
    else
      redirect_to trip
    end
  end

  private

  attr_reader :trip

  def set_trip
    @trip = Trip.find(params[:id])
  end

  def trip_params
    permitted = params.require(:trip).permit(policy(trip || Trip).permitted_attributes)
    permitted.delete(:cover_image) if permitted[:cover_image].blank?
    permitted
  end
end
