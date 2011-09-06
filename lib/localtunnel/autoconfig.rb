module LocalTunnel
  module AutoConfig
    class Base
      def self.inherited(base)
        super

        if base.name && base.name !~ /Base$/
          LocalTunnel::AutoConfig.subclasses << base
        end
      end
    end

    def self.subclasses
      @subclasses ||= []
    end

    def self.find(name)
      lookup(name)

      names = Hash[subclasses.map { |klass| [autoconfig_name(klass).downcase, klass] }]
      klass = names[name]
      return nil if klass.nil?

      configurator = klass.new
      if configurator.respond_to? :configure
        configurator
      else
        nil
      end
    end

    private

      def self.autoconfig_name(klass)
        if klass.name =~ /(\w*)AutoConfig$/
          underscore $1
        else
          klass.name
        end
      end

      def self.lookup(name)
        including_current = $LOAD_PATH.dup
        including_current << '.'
        including_current.each do |base|
          Dir[File.join(base, "localtunnel", "#{name}_auto_config.rb")].each do |path|
            begin
              path = path.sub("#{base}/", "")
              require path
            rescue Exception => e
              puts "   [Warning] Could not load autoconfig #{path.inspect}. Error: #{e.message}.\n#{e.backtrace.join("\n")}"
            end
          end
        end
      end

      def self.underscore(camel_cased_word)
        word = camel_cased_word.to_s.dup
        word.gsub!(/::/, '/')
        word.gsub!(/([A-Z]+)([A-Z][a-z])/,'\1_\2')
        word.gsub!(/([a-z\d])([A-Z])/,'\1_\2')
        word.tr!("-", "_")
        word.downcase!
        word
      end
  end
end
