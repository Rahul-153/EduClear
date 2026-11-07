import { Component, type ReactNode } from "react";

export default class Boundary extends Component<{ name: string; children: ReactNode }, { err: string | null }> {
  state = { err: null as string | null };
  static getDerivedStateFromError(e: Error) { return { err: e.message }; }
  render() {
    return this.state.err
      ? <section className="card" role="alert"><div className="empty">{this.props.name} could not be displayed.</div></section>
      : this.props.children;
  }
}
