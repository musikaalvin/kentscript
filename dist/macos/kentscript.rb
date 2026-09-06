class Kentscript < Formula
  desc "Systems programming language with C transpilation"
  homepage "https://github.com/musikaalvin/kentscript"
  version "3.1.0"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/musikaalvin/kentscript/raw/main/kentscript"
    else
      url "https://github.com/musikaalvin/kentscript/raw/main/kentscript"
    end
  end

  def install
    bin.install "kentscript"
  end

  test do
    system "kentscript", "--ks-version"
  end
end
