require 'rubygems'
require 'rake'
require 'echoe'

Echoe.new('localtunnel', '0.2') do |p|
  p.description    = "instant reverse tunnel for local web servers"
  p.url            = "http://github.com/progrium/localtunnel"
  p.author         = "Jeff Lindsay"
  p.email          = "jeff.lindsay@twilio.com"
  p.ignore_pattern = ["tmp/*", "script/*"]
  p.executable_pattern = ["bin/*"]
  p.runtime_dependencies = ["json >=1.2.4", "net-ssh >=2.0.22", "net-ssh-gateway >=1.0.1"]
  p.development_dependencies = []
end