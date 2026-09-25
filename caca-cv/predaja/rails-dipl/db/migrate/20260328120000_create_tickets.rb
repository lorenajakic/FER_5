class CreateTickets < ActiveRecord::Migration[8.0]
  def change
    create_table :tickets do |t|
      t.belongs_to :trip, null: false, foreign_key: { on_delete: :cascade }
      t.string :title, null: false
      t.integer :category, null: false
      t.date :date
      t.text :details
      t.integer :cost_cents
      t.string :cost_currency, default: "EUR"
      t.belongs_to :uploaded_by, null: false, foreign_key: { to_table: :users, on_delete: :cascade }

      t.timestamps
    end

    add_index :tickets, [ :trip_id, :category ]
  end
end
