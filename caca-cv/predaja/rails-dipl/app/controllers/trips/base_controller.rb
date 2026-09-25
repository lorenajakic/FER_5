module Trips
  class BaseController < ApplicationController
    before_action :set_trip
    before_action :authorize_trip_access!

    private

    attr_reader :trip

    def set_trip
      @trip = Trip.find(params[:trip_id])
    end

    def authorize_trip_access!
      authorize trip, :show?
    end
  end
end
