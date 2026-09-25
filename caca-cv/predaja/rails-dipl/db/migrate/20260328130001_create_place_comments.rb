class CreatePlaceComments < ActiveRecord::Migration[8.0]
  def change
    create_table :place_comments do |t|
      t.belongs_to :place, null: false, foreign_key: { on_delete: :cascade }
      t.belongs_to :user, null: false, foreign_key: { on_delete: :cascade }
      t.text :body, null: false

      t.timestamps
    end
  end
end
