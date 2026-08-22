const fs = require("fs");
const vm = require("vm");

const converterPath = process.argv[2];

if (!converterPath) {
  process.stderr.write("Missing converter script path.\n");
  process.exit(2);
}

const sandbox = {
  console,
  window: {},
  document: {
    addEventListener() {},
    getElementById() {
      return null;
    },
  },
  $() {
    return {
      val() {
        return "";
      },
      hasClass() {
        return false;
      },
      addClass() {
        return this;
      },
      removeClass() {
        return this;
      },
      bind() {
        return this;
      },
    };
  },
};

sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(converterPath, "utf8"), sandbox, {
  filename: converterPath,
});

let body = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  body += chunk;
});

process.stdin.on("end", () => {
  const input = JSON.parse(body || "[]");
  const output = input.map((value) => sandbox.ConvertToASCII(String(value ?? "")));
  process.stdout.write(JSON.stringify(output));
});
