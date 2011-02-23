require 'rubygems'
require 'net/ssh'
require 'net/ssh/gateway'
require 'net/http'
require 'uri'
require 'optparse'
require 'json'

class LocalTunnel

  attr_accessor :port, :key, :host

  def initialize(port, key)
    @port = port
    @key  = key
    @host = ""
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
    @host = resp['host']
    @tunnel = resp
    return resp
  rescue
    puts "   [Error] Unable to register tunnel. Perhaps service is down?"
    exit
  end

  def start_tunnel
    port = @port
    tunnel = @tunnel
    gateway = Net::SSH::Gateway.new(tunnel['host'], tunnel['user'])
    gateway.open_remote(port.to_i, '127.0.0.1', tunnel['through_port'].to_i) do |rp,rh|
      puts "   " << tunnel['banner'] if tunnel.has_key? 'banner'
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
