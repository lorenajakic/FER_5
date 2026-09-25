class LocalesController < ApplicationController
  skip_before_action :authenticate_user!

  def show
    loc = params[:locale].to_s
    session[:locale] = loc
    redirect_back_or_to root_path
  end
end
