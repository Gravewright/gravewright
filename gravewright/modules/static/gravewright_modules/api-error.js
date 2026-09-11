class ApiError extends Error {
  constructor(status, code) {
    super(code);
    this.status = status;
    this.code = code;
    this.name = "ApiError";
  }
  status;
  code;
}
class TransportError extends Error {
  constructor(path, options) {
    super("unreachable", options);
    this.path = path;
    this.name = "TransportError";
  }
  path;
  code = "unreachable";
}
export {
  ApiError,
  TransportError
};
