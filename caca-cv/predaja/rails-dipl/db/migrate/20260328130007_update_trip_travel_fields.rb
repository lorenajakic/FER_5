class UpdateTripTravelFields < ActiveRecord::Migration[8.0]
  def up
    remove_column :trips, :accommodation_latitude, :decimal if column_exists?(:trips, :accommodation_latitude)
    remove_column :trips, :accommodation_longitude, :decimal if column_exists?(:trips, :accommodation_longitude)

    return if column_exists?(:trips, :arrival_transport_mode)

    change_table :trips, bulk: true do |t|
      t.string :arrival_transport_mode
      t.datetime :arrival_at
      t.string :arrival_details
      t.string :departure_transport_mode
      t.datetime :departure_at
      t.string :departure_details
    end
  end

  def down
    change_table :trips, bulk: true do |t|
      t.decimal :accommodation_latitude, precision: 10, scale: 7 unless column_exists?(:trips, :accommodation_latitude)
      t.decimal :accommodation_longitude, precision: 10, scale: 7 unless column_exists?(:trips, :accommodation_longitude)
    end

    remove_column :trips, :arrival_transport_mode, :string if column_exists?(:trips, :arrival_transport_mode)
    remove_column :trips, :arrival_at, :datetime if column_exists?(:trips, :arrival_at)
    remove_column :trips, :arrival_details, :string if column_exists?(:trips, :arrival_details)
    remove_column :trips, :departure_transport_mode, :string if column_exists?(:trips, :departure_transport_mode)
    remove_column :trips, :departure_at, :datetime if column_exists?(:trips, :departure_at)
    remove_column :trips, :departure_details, :string if column_exists?(:trips, :departure_details)
  end
end
