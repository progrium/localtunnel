require 'rubygems'
require 'net/ssh'
require 'net/ssh/gateway'
require 'net/http'
require 'uri'
require 'json'

require 'localtunnel/net_ssh_gateway_patch'

module LocalTunnel; end

class LocalTunnel::Tunnel

  SHELL_HOOK_FILE = "./.localtunnel_callback"

  attr_accessor :port, :key, :host

  def initialize(url, port, key, auth)
    @url = url
    @port = port
    @key  = key
    @auth = auth
    @host = ""
  end

  def register_tunnel
    uri = URI.parse(@url)
    if @key
      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'
      req = Net::HTTP::Post.new(uri.request_uri) 
      if @auth
        request.basic_auth(auth[0], auth[1])
      end
      req.set_form_data({"key" => @key})
      resp = JSON.parse(http.request(req).body)
    else
      resp = JSON.parse(Net::HTTP.get(uri))
    end
    if resp.has_key? 'error'
      puts "   [Error] #{resp['error']}"
      exit
    end
    @host = resp['host'].split(':').first
    @tunnel = resp
    return resp
  end

  def start_tunnel
    port = @port
    tunnel = @tunnel
    gateway = Net::SSH::Gateway.new(@host, tunnel['user'])
    gateway.open_remote(port.to_i, '127.0.0.1', tunnel['through_port'].to_i) do |rp,rh|
      puts "   " << tunnel['banner'] if tunnel.has_key? 'banner'
      if File.exists?(File.expand_path(SHELL_HOOK_FILE))
        system "#{SHELL_HOOK_FILE} ""#{tunnel['host']}""" if File.exists?(File.expand_path(SHELL_HOOK_FILE))
        if !$?.success?
          puts "   An error occurred executing the callback hook #{SHELL_HOOK_FILE}"
          puts "   (Make sure it is executable)"
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
end
