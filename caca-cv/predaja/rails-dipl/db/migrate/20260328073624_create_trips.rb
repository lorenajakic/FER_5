class CreateTrips < ActiveRecord::Migration[8.0]
  def change
    create_table :trips do |t|
      t.string :title, null: false
      t.string :destination, null: false
      t.date :start_date, null: false
      t.date :end_date, null: false
      t.integer :status, null: false, default: 0
      t.belongs_to :creator, null: false, foreign_key: { to_table: :users, on_delete: :cascade }

      t.timestamps
    end

    add_index :trips, :status
    add_index :trips, :start_date
  end
end
