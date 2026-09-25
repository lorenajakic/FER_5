class AddAccommodationFieldsToTrips < ActiveRecord::Migration[8.0]
  def change
    change_table :trips, bulk: true do |t|
      t.string :accommodation_address
      t.decimal :accommodation_latitude, precision: 10, scale: 7
      t.decimal :accommodation_longitude, precision: 10, scale: 7
    end
  end
end
