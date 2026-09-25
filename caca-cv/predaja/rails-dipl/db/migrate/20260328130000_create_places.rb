class CreatePlaces < ActiveRecord::Migration[8.0]
  def change
    create_table :places do |t|
      t.belongs_to :trip, null: false, foreign_key: { on_delete: :cascade }
      t.string :name, null: false
      t.string :address
      t.decimal :latitude, precision: 10, scale: 7, null: false
      t.decimal :longitude, precision: 10, scale: 7, null: false
      t.integer :category, null: false, default: 6
      t.integer :estimated_duration_minutes
      t.belongs_to :added_by, null: false, foreign_key: { to_table: :users, on_delete: :cascade }

      t.timestamps
    end
  end
end
