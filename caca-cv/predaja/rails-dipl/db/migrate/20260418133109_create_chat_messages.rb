class CreateChatMessages < ActiveRecord::Migration[8.0]
  def change
    create_table :chat_messages do |t|
      t.references :trip, null: false, foreign_key: true
      t.string :role, null: false, default: "user"
      t.text :content
      t.jsonb :plan_json

      t.timestamps
    end
    add_index :chat_messages, [:trip_id, :created_at]
  end
end
