class GeocodingController < ApplicationController
  def autocomplete
    results = Geocoding::Autocomplete.new(
      query: params[:q],
      limit: 5,
      lat: params[:lat],
      lon: params[:lon]
    ).call
    render json: results
  end

  def reverse
    place = Geocoding::Reverse.new(lat: params[:lat], lon: params[:lon]).call
    render json: place || {}
  end
end
