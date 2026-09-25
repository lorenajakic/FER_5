class AddAccommodationCheckinCheckoutToTrips < ActiveRecord::Migration[8.0]
  def change
    add_column :trips, :accommodation_checkin_at, :datetime
    add_column :trips, :accommodation_checkout_at, :datetime
  end
end
