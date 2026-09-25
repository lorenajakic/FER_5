class RemoveEstimatedDurationMinutesFromPlaces < ActiveRecord::Migration[8.0]
  def change
    remove_column :places, :estimated_duration_minutes, :integer
  end
end
