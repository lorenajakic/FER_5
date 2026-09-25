Rails.application.routes.draw do
  get "locale/:locale", to: "locales#show", as: :locale_switch,
                        constraints: { locale: /en|hr/ }

  devise_for :users

  resource :profile, only: [ :show, :edit, :update ]

  resources :trips do
    member do
      patch :update_status
    end
    resources :places, only: [ :index, :create, :destroy ], module: :trips do
      resources :comments, only: [ :create, :destroy ], module: :places, controller: :comments
    end
    resources :tickets, only: [ :index, :new, :create, :show, :edit, :update, :destroy ], module: :trips
    resources :chat_messages, only: [ :index, :create ], module: :trips, path: :chat
    resource :itinerary, only: [ :show, :update ], module: :trips
  end

  get "geocoding/autocomplete", to: "geocoding#autocomplete"
  get "geocoding/reverse", to: "geocoding#reverse"

  resources :invitations, only: [ :index, :create ] do
    member do
      post :accept
      post :decline
    end
  end

  authenticated :user do
    root "dashboard#index", as: :authenticated_root
  end
  devise_scope :user do
    root "devise/sessions#new"
  end

  get "up" => "rails/health#show", as: :rails_health_check
end
