class CreateTripInvitations < ActiveRecord::Migration[8.0]
  def change
    create_table :trip_invitations do |t|
      t.belongs_to :trip, null: false, foreign_key: { on_delete: :cascade }
      t.citext :email, null: false
      t.string :token, null: false, index: { unique: true }
      t.datetime :accepted_at
      t.belongs_to :invited_by, null: false, foreign_key: { to_table: :users, on_delete: :cascade }

      t.timestamps
    end

    add_index :trip_invitations, [ :trip_id, :email ], unique: true
  end
end
