class CreateItineraries < ActiveRecord::Migration[8.0]
  def change
    create_table :itineraries do |t|
      t.references :trip, null: false, foreign_key: true
      t.jsonb :plan_json, null: false, default: {}

      t.timestamps
    end
    add_index :itineraries, :trip_id, unique: true, name: "index_itineraries_trip_id_unique"
  end
end
