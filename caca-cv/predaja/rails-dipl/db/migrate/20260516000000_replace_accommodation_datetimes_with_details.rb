class ReplaceAccommodationDatetimesWithDetails < ActiveRecord::Migration[8.0]
  def change
    remove_column :trips, :accommodation_checkin_at, :datetime
    remove_column :trips, :accommodation_checkout_at, :datetime
    add_column :trips, :accommodation_details, :text
  end
end
