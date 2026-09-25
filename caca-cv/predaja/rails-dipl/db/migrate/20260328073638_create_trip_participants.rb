class CreateTripParticipants < ActiveRecord::Migration[8.0]
  def change
    create_table :trip_participants do |t|
      t.belongs_to :trip, null: false, foreign_key: { on_delete: :cascade }
      t.belongs_to :user, null: false, foreign_key: { on_delete: :cascade }

      t.timestamps
    end

    add_index :trip_participants, [ :trip_id, :user_id ], unique: true
  end
end
