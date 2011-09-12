require 'rubygems'
require 'net/ssh'
require 'net/ssh/gateway'
require 'net/http'
require 'uri'
require 'json'

require 'localtunnel/net_ssh_gateway_patch'

module LocalTunnel; end

# This global method is what a configuration plugin uses to register itself
def configure(name, &block)
  LocalTunnel::Tunnel.config[name.downcase] = block
end

class LocalTunnel::Configuration
  attr_accessor :host

  def initialize(host)
    @host = host
  end
end

class LocalTunnel::Tunnel

  attr_accessor :port, :key, :host, :autoconfig

  def initialize(port, key, autoconfig_name)
    @port = port
    @key  = key
    @host = ""
    @autoconfig = autoconfig_name
  end

  def register_tunnel(key=@key)
    url = URI.parse("http://open.localtunnel.com/")
    if key
      resp = JSON.parse(Net::HTTP.post_form(url, {"key" => key}).body)
    else
      resp = JSON.parse(Net::HTTP.get(url))
    end
    if resp.has_key? 'error'
      puts "   [Error] #{resp['error']}"
      exit
    end
    @host = resp['host'].split(':').first
    @tunnel = resp
    return resp
  rescue
    puts "   [Error] Unable to register tunnel. Perhaps service is down?"
    exit
  end

  def start_tunnel
    port = @port
    tunnel = @tunnel
    gateway = Net::SSH::Gateway.new(@host, tunnel['user'])
    gateway.open_remote(port.to_i, '127.0.0.1', tunnel['through_port'].to_i) do |rp,rh|
      puts "   " << tunnel['banner'] if tunnel.has_key? 'banner'
      if @autoconfig
        LocalTunnel::Tunnel.load_config(@autoconfig)
        do_config = LocalTunnel::Tunnel.config[@autoconfig.downcase]
        if do_config
          config = LocalTunnel::Configuration.new(tunnel['host'])
          do_config.call(config)
        else
          puts "   [Warning] Unable to find an automatic configuration plugin for '#{@autoconfig}'"
        end
      end
      puts "   Port #{port} is now publicly accessible from http://#{tunnel['host']} ..."
      begin
        sleep 1 while true
      rescue Interrupt
        gateway.close_remote(rp, rh)
        exit
      end
    end
  rescue Net::SSH::AuthenticationFailed
    possible_key = Dir[File.expand_path('~/.ssh/*.pub')].first
    puts "   Failed to authenticate. If this is your first tunnel, you need to"
    puts "   upload a public key using the -k option. Try this:\n\n"
    puts "   localtunnel -k #{possible_key ? possible_key : '~/path/to/key'} #{port}"
    exit
  end

  def self.config
    @config ||= {}
  end

  def self.load_config(name)
    path = File.join('.', 'localtunnel', "#{name}.rb")
    begin
      require path
    rescue Exception => e
      puts "   [Warning] Could not load configuration #{path.inspect}. Error: #{e.message}.\n#{e.backtrace.join("\n")}"
    end
  end
end
