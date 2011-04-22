Gem::Specification.new do |s|
  s.name      = "localtunnel"
  s.version   = "0.2"
  s.authors   = ["Jeff Lindsay"]
  s.email     = "progrium@twilio.com"
  s.homepage  = "http://github.com/progrium/localtunnel"
  s.summary   = ""
  s.description  = <<-EOS.strip
LocalTunnel
  EOS

  s.add_dependency "net-ssh"
  s.add_dependency "net-ssh-gateway"

  s.files      = Dir['lib/*']
  s.test_files = Dir['test/**/*.rb']
end

