ENV["BUNDLE_GEMFILE"] ||= File.expand_path("../Gemfile", __dir__)

require "bundler/setup"
require "bootsnap/setup"
require "dotenv"
Dotenv.load
