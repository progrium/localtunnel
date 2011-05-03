# -*- encoding: utf-8 -*-

Gem::Specification.new do |s|
  s.name = %q{localtunnel}
  s.version = "0.2"

  s.required_rubygems_version = Gem::Requirement.new(">= 1.2") if s.respond_to? :required_rubygems_version=
  s.authors = ["Jeff Lindsay"]
  s.cert_chain = ["/Users/progrium/.gem/gem-public_cert.pem"]
  s.date = %q{2011-05-02}
  s.default_executable = %q{localtunnel}
  s.description = %q{instant public tunnel to your local web server}
  s.email = %q{jeff.lindsay@twilio.com}
  s.executables = ["localtunnel"]
  s.extra_rdoc_files = ["lib/localtunnel.rb", "bin/localtunnel"]
  s.files = ["Rakefile", "lib/localtunnel.rb", "bin/localtunnel", "server.py", "Manifest", "localtunnel.gemspec"]
  s.homepage = %q{http://github.com/progrium/localtunnel}
  s.rdoc_options = ["--line-numbers", "--inline-source", "--title", "Localtunnel", "--main", "README.rdoc"]
  s.require_paths = ["lib"]
  s.rubyforge_project = %q{localtunnel}
  s.rubygems_version = %q{1.4.1}
  s.signing_key = %q{/Users/progrium/.gem/gem-private_key.pem}
  s.summary = %q{instant public tunnel to your local web server}

  if s.respond_to? :specification_version then
    s.specification_version = 3

    if Gem::Version.new(Gem::VERSION) >= Gem::Version.new('1.2.0') then
      s.add_runtime_dependency(%q<json>, [">= 1.2.4"])
      s.add_runtime_dependency(%q<net-ssh>, [">= 2.0.22"])
      s.add_runtime_dependency(%q<net-ssh-gateway>, [">= 1.0.1"])
    else
      s.add_dependency(%q<json>, [">= 1.2.4"])
      s.add_dependency(%q<net-ssh>, [">= 2.0.22"])
      s.add_dependency(%q<net-ssh-gateway>, [">= 1.0.1"])
    end
  else
    s.add_dependency(%q<json>, [">= 1.2.4"])
    s.add_dependency(%q<net-ssh>, [">= 2.0.22"])
    s.add_dependency(%q<net-ssh-gateway>, [">= 1.0.1"])
  end
end
