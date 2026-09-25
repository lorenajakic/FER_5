class AddAccommodationCoordinatesToTrips < ActiveRecord::Migration[8.0]
  def change
    add_column :trips, :accommodation_latitude, :decimal, precision: 10, scale: 6
    add_column :trips, :accommodation_longitude, :decimal, precision: 10, scale: 6
  end
end
