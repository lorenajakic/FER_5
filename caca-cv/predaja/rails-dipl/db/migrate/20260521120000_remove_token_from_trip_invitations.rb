class RemoveTokenFromTripInvitations < ActiveRecord::Migration[8.0]
  def change
    remove_index :trip_invitations, :token
    remove_column :trip_invitations, :token, :string
  end
end
