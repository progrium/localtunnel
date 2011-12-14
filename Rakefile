require 'rubygems'
require 'rake'
require 'echoe'

Echoe.new('localtunnel', '0.4') do |p|
  p.description    = "instant public tunnel to your local web server"
  p.url            = "http://github.com/progrium/localtunnel"
  p.author         = "Jeff Lindsay"
  p.email          = "jeff.lindsay@twilio.com"
  p.rdoc_pattern   = //
  p.rdoc_options   = []
  p.ignore_pattern = ["tmp/*", "script/*", "*.py*"]
  p.executable_pattern = ["bin/*"]
  p.runtime_dependencies = ["json >=1.2.4", "net-ssh >=2.0.22", "net-ssh-gateway >=1.0.1"]
  p.development_dependencies = []
end
