module LocalTunnel
  module AutoConfig
    def self.subclasses
      @subclasses ||= []
    end

    def self.find(name)
      lookup(name)

      names = Hash[subclasses.map { |klass| [klass.respond_to?(:autoconfig_name) ? klass.autoconfig_name.downcase : klass.name.downcase, klass] }]
      klass = names[name]
      return nil if klass.nil?

      configurator = klass.new
      if configurator.respond_to? :configure
        configurator
      else
        nil
      end
    end

    def self.lookup(name)
      $LOAD_PATH.each do |base|
        Dir[File.join(base, "localtunnel", "**", "#{name}_autoconfig.rb")].each do |path|
          begin
            path = path.sub("#{base}/", "")
            require path
          rescue Exception
            # No problem
          end
        end
      end
    end
  end

  class Base
    def self.inherited(base)
      super

      if base.name && base.name !~ /Base$/
        LocalTunnel::AutoConfig.subclasses << base
      end
    end
  end
end

